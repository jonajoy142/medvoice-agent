"""
Improved Intent Service with session memory and doctor context handling
"""

import re
from datetime import datetime
from typing import Dict, Any
from app.repositories import appointment_repository, doctor_repository, patient_repository

class IntentService:
    def __init__(self):
        pass

    PATIENT_RECORD_VERIFICATION_RESPONSE = (
        "I can help check a patient chart, but I'll need a verified patient ID or phone number plus DOB first."
    )
    
    def detect_intent(self, text: str) -> str:
        """Detect user intent from text"""
        text_lower = text.lower()
        
        # Greeting patterns
        greeting_patterns = [
            r'\b(?:hello|hi|hey)\b|\bgood\s+(?:morning|afternoon|evening)\b',
            r'\bhow are you\b|\bwhat can you do\b',
        ]
        
        for pattern in greeting_patterns:
            if re.search(pattern, text_lower):
                return "greeting"
        
        # Patient chart/record lookup patterns must run before appointment
        # routing so historical visit requests are not treated as bookings.
        patient_patterns = [
            r'\bcheck\s+(?:my\s+)?(?:latest\s+)?chart\b',
            r'\blatest\s+chart\b',
            r'\bmedical\s+chart\b',
            r'\bmy\s+records?\b',
            r'\bpatient\s+records?\b',
            r'\bmedical\s+records?\b',
            r'\blatest\s+reports?\b',
            r'\bprevious\s+visit\b',
            r'\bearlier\s+appointment\b',
            r'\bpatient\b',
            r'\blookup\b',
            r'\bfind\s+.*patient\b',
            r'\bmedical\s+record\b',
            r'\bopid\b',
            r'\bmy\s+.*information\b',
        ]

        for pattern in patient_patterns:
            if re.search(pattern, text_lower):
                return "patient_lookup"

        emergency_patterns = [
            r'\bemergency\b|chest pain|cannot breathe|unconscious|severe bleeding|stroke',
        ]
        for pattern in emergency_patterns:
            if re.search(pattern, text_lower):
                return "emergency_escalation"

        reschedule_patterns = [
            r'\breschedule\b|move my appointment|change my appointment',
        ]
        for pattern in reschedule_patterns:
            if re.search(pattern, text_lower):
                return "reschedule_appointment"

        intake_patterns = [
            r'\bintake\b|pre[- ]?visit|before my visit|visit reason',
        ]
        for pattern in intake_patterns:
            if re.search(pattern, text_lower):
                return "patient_intake"

        follow_up_patterns = [
            r'\bfollow[- ]?up\b|after consultation|after my visit|\bcallback\b|call me back',
        ]
        for pattern in follow_up_patterns:
            if re.search(pattern, text_lower):
                return "follow_up"

        visit_reminder_patterns = [
            r'\bvisit reminder\b|remind me.*\bvisit\b|remind me.*\bappointment\b',
        ]
        for pattern in visit_reminder_patterns:
            if re.search(pattern, text_lower):
                return "visit_reminder"

        medicine_reminder_patterns = [
            r'\bmedicine reminder\b|\bmedication reminder\b|remind me.*\b(?:medicine|medication|tablet|pill)\b',
        ]
        for pattern in medicine_reminder_patterns:
            if re.search(pattern, text_lower):
                return "medicine_reminder"

        lab_patterns = [
            r'\blab report\b|report ready|test results ready',
        ]
        for pattern in lab_patterns:
            if re.search(pattern, text_lower):
                return "lab_report_ready"

        billing_patterns = [
            r'\bbilling\b|payment reminder|amount due|invoice',
        ]
        for pattern in billing_patterns:
            if re.search(pattern, text_lower):
                return "billing_payment_reminder"

        routing_patterns = [
            r'\broute\b|connect me to|which department|department|speak to a nurse|talk to a nurse|\bnurse\b',
        ]
        for pattern in routing_patterns:
            if re.search(pattern, text_lower):
                return "department_routing"

        language_patterns = [
            r'\bmalayalam\b|\bhindi\b|\btamil\b|\btelugu\b|which languages|support.*language',
        ]
        for pattern in language_patterns:
            if re.search(pattern, text_lower):
                return "language_support"

        cancel_patterns = [
            r'\bcancel\b.*\bappointment\b',
        ]
        for pattern in cancel_patterns:
            if re.search(pattern, text_lower):
                return "cancel_appointment"

        # Appointment booking patterns
        booking_patterns = [
            r'book|schedule|make an appointment|appointment',
            r'want to see|need to visit|consultation',
        ]
        
        for pattern in booking_patterns:
            if re.search(pattern, text_lower):
                return "book_appointment"
        
        # Availability check patterns
        availability_patterns = [
            r'available|availability|when.*free|schedule|time slots|\bslots?\b',
            r'who.*available|doctor.*time',
        ]
        
        for pattern in availability_patterns:
            if re.search(pattern, text_lower):
                return "check_availability"

        faq_patterns = [
            r'visiting hours|visitor hours|hospital hours',
            r'where.*located|location|address',
        ]

        for pattern in faq_patterns:
            if re.search(pattern, text_lower):
                return "faq"
        
        # Doctor info patterns
        doctor_patterns = [
            r'doctor|physician|specialist',
            r'which.*doctor|who.*available',
        ]
        
        for pattern in doctor_patterns:
            if re.search(pattern, text_lower):
                return "doctor_info"
        
        # Goodbye patterns
        goodbye_patterns = [
            r'bye|goodbye|see you|thank.*bye|that.*all',
        ]
        
        for pattern in goodbye_patterns:
            if re.search(pattern, text_lower):
                return "goodbye"
        
        return "general"
    
    def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract entities from user text"""
        entities = {"text": text}
        
        # Extract OPID (6-digit numbers) - handle number words
        number_words = {
            'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
            'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'double': '2'
        }
        
        # Replace number words with digits
        text_normalized = text.lower()
        for word, digit in number_words.items():
            text_normalized = text_normalized.replace(word, digit)
        
        # Extract 6-digit OPID from normalized text
        opid_match = re.search(r'\b(\d{6})\b', text_normalized)
        if opid_match:
            entities["opid"] = opid_match.group(1)
        
        # Extract time patterns
        time_patterns = [
            r'(\d{1,2}:\d{2}\s*(?:am|pm))',
            r'(\d{1,2})\s*(am|pm)',
            r'(morning|afternoon|evening)'
        ]
        
        text_lower = text.lower()
        for pattern in time_patterns:
            match = re.search(pattern, text_lower)
            if match:
                entities["time"] = match.group(1)
                break
        
        # Extract doctor name
        doctor_match = re.search(r'dr\.?\s*([a-zA-Z]+)', text_lower)
        if doctor_match:
            entities["doctor_name"] = doctor_match.group(1).title()
        
        # Extract specialization
        specializations = ["dermatologist", "general", "cardiologist", "pediatrician"]
        for spec in specializations:
            if spec in text_lower:
                entities["specialization"] = spec
                break
        
        return entities
    
    def route_intent(self, intent: str, entities: Dict[str, Any], session: Dict[str, Any] = None) -> Dict[str, Any]:
        """Route intent to appropriate action and return response"""
        if intent == "greeting":
            # Personalized greeting if we know the patient
            if session and session.get("patient_name"):
                return {
                    "action": "greet",
                    "response": f"Hello {session['patient_name']}! How can I help you today?",
                    "data": None
                }
            else:
                return {
                    "action": "greet",
                    "response": "Hello! I'm your hospital assistant. How can I help you today?",
                    "data": None
                }
        
        elif intent == "patient_lookup":
            return self._handle_patient_lookup(entities)
        
        elif intent == "book_appointment":
            return self._handle_book_appointment(entities, session)
        
        elif intent == "check_availability":
            return self._handle_check_availability(entities, session)
        
        elif intent == "doctor_info":
            return self._handle_doctor_info(entities, session)

        elif intent == "faq":
            return self._handle_faq(entities)

        elif intent in {
            "reschedule_appointment",
            "patient_intake",
            "follow_up",
            "medicine_reminder",
            "visit_reminder",
            "lab_report_ready",
            "billing_payment_reminder",
            "department_routing",
            "language_support",
            "cancel_appointment",
            "human_handoff",
            "emergency_escalation",
        }:
            return self._handle_workflow(intent, entities)
        
        elif intent == "goodbye":
            return {
                "action": "goodbye",
                "response": "Goodbye! Take care and feel better soon.",
                "data": None
            }
        
        else:
            return {
                "action": "general",
                "response": "I can help you book appointments, check availability, or find patient information. What would you like to do?",
                "data": None
            }

    def _handle_faq(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """FAQ must be grounded by uploaded KB content, not static answers."""
        return {
            "action": "faq_content_gap",
            "response": "I could not find a grounded hospital knowledge-base answer. I will route this to staff.",
            "data": {"source": "knowledge_base", "content_gap": True, "question": entities.get("text")},
        }

    def _handle_workflow(self, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        from app.workflows import workflow_engine

        if intent == "emergency_escalation":
            return {
                "action": "emergency_escalation",
                "response": "This may be urgent. I am escalating immediately. If this is life-threatening, please call emergency services now.",
                "data": {"escalation": True, "severity": "critical"},
            }
        if intent == "language_support":
            return {
                "action": "language_support",
                "response": "I can help in English here. Malayalam, Hindi, Tamil, and Telugu voice support can be enabled when the production voice provider is connected.",
                "data": {"languages": ["en-IN", "ml-IN", "hi-IN", "ta-IN", "te-IN"]},
            }
        if intent == "cancel_appointment":
            return {
                "action": "request_appointment_reference",
                "response": "I can help request a cancellation. Please share the appointment reference or patient ID so reception can verify it.",
                "data": {"missing": ["appointment_reference_or_patient_identifier"]},
            }

        slots = {
            "patient_identifier": entities.get("opid"),
            "department_or_specialization": entities.get("specialization"),
            "preferred_time": entities.get("time"),
            "grounded_answer": entities.get("grounded_answer"),
        }
        result = workflow_engine.route(intent, slots)
        if result.escalation_required:
            return {
                "action": "human_handoff",
                "response": "I will connect you with hospital staff for this request.",
                "data": {"workflow": result.workflow, "state": result.state, "escalation": True},
            }
        if result.missing_slots:
            friendly_missing = {
                "reschedule_appointment": "I can help request a change. Please share the appointment reference and the new time you prefer.",
                "follow_up": "I can arrange a follow-up callback. Please share the patient ID or phone number so reception can verify the request.",
                "medicine_reminder": "I can help with visit reminders, but medication reminders must follow a doctor-approved script. I can connect you to reception.",
                "visit_reminder": "I can help with visit reminders. Please share the patient ID or appointment reference.",
                "billing_payment_reminder": "I can connect you to billing. Please share a billing reference if you have one.",
                "department_routing": "I can connect you to reception so they can route you to the right clinical team.",
            }
            return {
                "action": "request_more_info",
                "response": friendly_missing.get(intent, f"I need {', '.join(result.missing_slots)} to continue this workflow."),
                "data": {"workflow": result.workflow, "missing": result.missing_slots},
            }
        return {
            "action": result.response_template or "workflow_ready",
            "response": "I have the required details and will proceed within the approved workflow.",
            "data": {"workflow": result.workflow, "state": result.state},
        }
    
    def _handle_patient_lookup(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Handle patient lookup intent"""
        if "opid" in entities:
            patient = patient_repository().get_patient(entities["opid"])
            if patient:
                return {
                    "action": "patient_found",
                    "response": f"Found: {patient['name']}, OPID: {entities['opid']}. Medical history: {', '.join(patient['history'])}",
                    "data": patient
                }
            else:
                return {
                    "action": "patient_not_found",
                    "response": f"No patient found with OPID {entities['opid']}. Please check the OPID and try again.",
                    "data": None
                }
        else:
            return {
                "action": "request_patient_verification",
                "response": self.PATIENT_RECORD_VERIFICATION_RESPONSE,
                "data": {"missing": ["verified_patient_identifier"]}
            }
    
    def _handle_book_appointment(self, entities: Dict[str, Any], session: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle appointment booking intent"""
        # Check if OPID is already in session
        session_opid = session.get("opid") if session else None
        opid = entities.get("opid") or session_opid
        
        if not opid:
            return {
                "action": "request_opid",
                "response": "To book an appointment, I need your OPID first. Could you please provide your 6-digit OPID?",
                "data": {"missing": ["opid"]}
            }
        
        patient = patient_repository().get_patient(opid)
        if not patient:
            return {
                "action": "patient_not_found",
                "response": f"I can't find your record with OPID {opid}. Please check your OPID and try again.",
                "data": None
            }
        
        # Check if we have enough info to book
        missing_info = []
        if "specialization" not in entities:
            missing_info.append("specialization")
        if "time" not in entities:
            missing_info.append("preferred time")
        
        if missing_info:
            return {
                "action": "request_more_info",
                "response": f"I need a bit more information. Please provide: {', '.join(missing_info)}.",
                "data": {"missing": missing_info}
            }
        
        # Create appointment (simplified)
        appointment_data = {
            "patient_opid": opid,
            "patient_name": patient["name"],
            "specialization": entities["specialization"],
            "requested_time": entities["time"],
            "status": "pending"
        }
        
        appointment = appointment_repository().add_appointment(appointment_data)
        
        return {
            "action": "appointment_booked",
            "response": f"Great! I've requested an appointment for {patient['name']} with {entities['specialization']} at {entities['time']}. We'll confirm it shortly.",
            "data": appointment
        }
    
    def _handle_check_availability(self, entities: Dict[str, Any], session: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle availability check intent"""
        specialization = entities.get("specialization", "dermatologist")
        doctor_name = entities.get("doctor_name")
        doctors = self._find_doctors(doctor_name=doctor_name, specialization=specialization)
        
        if not doctors:
            label = f"Dr. {doctor_name}" if doctor_name else specialization
            return {
                "action": "no_doctors",
                "response": f"I don't currently have today's {label} schedule available. Would you like me to connect you to reception?",
                "data": None
            }

        text_lower = entities.get("text", "").lower()
        if "today" in text_lower:
            today = datetime.now().strftime("%A")
            today_doctors = [doc for doc in doctors if today in doc.get("available_days", [])]
            if not today_doctors:
                label = f"Dr. {doctor_name}" if doctor_name else specialization
                return {
                    "action": "no_doctors_today",
                    "response": f"I don't currently have today's {label} schedule available. Would you like me to connect you to reception?",
                    "data": {"doctors": doctors, "day": today},
                }
            doctors = today_doctors
        
        # Store doctor list in session for "that doctor" references
        if session:
            doctor_names = [doc['name'] for doc in doctors]
            session["last_doctor_list"] = doctor_names
        
        # Create natural response
        first_doctor = doctors[0]
        available_slots = first_doctor['slots'][:2]  # Show first 2 slots
        available_days = [datetime.now().strftime("%A")] if "today" in text_lower else first_doctor['available_days'][:2]
        
        doctor_name = first_doctor["name"]
        if not doctor_name.lower().startswith("dr."):
            doctor_name = f"Dr. {doctor_name}"
        response = f"Yes, {doctor_name} is available at {', '.join(available_slots)} on {', '.join(available_days)}."
        
        return {
            "action": "availability_info",
            "response": response,
            "data": {"doctors": doctors}
        }

    def _find_doctors(self, doctor_name: str | None = None, specialization: str | None = None) -> list[Dict[str, Any]]:
        if doctor_name:
            all_doctors = doctor_repository().get_doctors()
            if isinstance(all_doctors, dict):
                doctors = [doctor for group in all_doctors.values() for doctor in group]
            else:
                doctors = all_doctors or []
            return [
                doctor for doctor in doctors
                if doctor_name.lower() in (doctor.get("name") or "").lower()
            ]

        return doctor_repository().get_doctors(specialization) or []
    
    def _handle_doctor_info(self, entities: Dict[str, Any], session: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle doctor information request"""
        specialization = entities.get("specialization", "dermatologist")
        doctors = doctor_repository().get_doctors(specialization)
        
        if not doctors:
            return {
                "action": "no_doctors",
                "response": f"I don't have any {specialization} doctors available right now.",
                "data": None
            }
        
        # Check for "that doctor" reference
        text_lower = entities.get("text", "").lower()
        if "that doctor" in text_lower and session and session.get("last_doctor_list"):
            # Reference the last mentioned doctor
            last_doctors = session["last_doctor_list"]
            if last_doctors:
                doctor_name = last_doctors[0]  # Use first mentioned doctor
                safe_name = doctor_name if doctor_name.lower().startswith("dr.") else f"Dr. {doctor_name}"
                return {
                    "action": "doctor_info",
                    "response": f"Yes, I was referring to {safe_name}.",
                    "data": {"doctors": doctors}
                }
        
        # Natural response with first doctor
        first_doctor = doctors[0]
        safe_first_name = first_doctor["name"]
        if not safe_first_name.lower().startswith("dr."):
            safe_first_name = f"Dr. {safe_first_name}"
        if len(doctors) == 1:
            response = f"Yes, {safe_first_name} is our {specialization} specialist."
        else:
            response = f"Yes, we have {safe_first_name} and {len(doctors)-1} other {specialization} specialists available."
        
        return {
            "action": "doctor_list",
            "response": response,
            "data": {"doctors": doctors}
        }

# Global instance
intent_service = IntentService()
