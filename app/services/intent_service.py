"""
Improved Intent Service with session memory and doctor context handling
"""

import re
from typing import Dict, Any
from app.repo.mock_db import get_patient, get_doctors, add_appointment

class IntentService:
    def __init__(self):
        pass
    
    def detect_intent(self, text: str) -> str:
        """Detect user intent from text"""
        text_lower = text.lower()
        
        # Greeting patterns
        greeting_patterns = [
            r'hello|hi|hey|good morning|good afternoon|good evening',
            r'how are you|what can you do',
        ]
        
        for pattern in greeting_patterns:
            if re.search(pattern, text_lower):
                return "greeting"
        
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
            r'available|when.*free|schedule|time slots',
            r'who.*available|doctor.*time',
        ]
        
        for pattern in availability_patterns:
            if re.search(pattern, text_lower):
                return "check_availability"
        
        # Patient lookup patterns
        patient_patterns = [
            r'patient|lookup|find.*patient|medical record',
            r'opid|my.*information',
        ]
        
        for pattern in patient_patterns:
            if re.search(pattern, text_lower):
                return "patient_lookup"
        
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
        entities = {}
        
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
    
    def _handle_patient_lookup(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Handle patient lookup intent"""
        if "opid" in entities:
            patient = get_patient(entities["opid"])
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
                "action": "request_opid",
                "response": "I need your OPID to look up your information. Could you please provide your 6-digit OPID?",
                "data": None
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
        
        patient = get_patient(opid)
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
        
        appointment = add_appointment(appointment_data)
        
        return {
            "action": "appointment_booked",
            "response": f"Great! I've requested an appointment for {patient['name']} with {entities['specialization']} at {entities['time']}. We'll confirm it shortly.",
            "data": appointment
        }
    
    def _handle_check_availability(self, entities: Dict[str, Any], session: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle availability check intent"""
        specialization = entities.get("specialization", "dermatologist")
        doctors = get_doctors(specialization)
        
        if not doctors:
            return {
                "action": "no_doctors",
                "response": f"No {specialization} doctors available right now. Would you like me to check another specialization?",
                "data": None
            }
        
        # Store doctor list in session for "that doctor" references
        if session:
            doctor_names = [doc['name'] for doc in doctors]
            from app.repo.mock_db import update_session
            update_session(session.get("id", ""), {"last_doctor_list": doctor_names})
        
        # Create natural response
        first_doctor = doctors[0]
        available_slots = first_doctor['slots'][:2]  # Show first 2 slots
        available_days = first_doctor['available_days'][:2]  # Show first 2 days
        
        response = f"Yes, Dr. {first_doctor['name']} is available at {', '.join(available_slots)} on {', '.join(available_days)}."
        
        return {
            "action": "availability_info",
            "response": response,
            "data": {"doctors": doctors}
        }
    
    def _handle_doctor_info(self, entities: Dict[str, Any], session: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle doctor information request"""
        specialization = entities.get("specialization", "dermatologist")
        doctors = get_doctors(specialization)
        
        if not doctors:
            return {
                "action": "no_doctors",
                "response": f"I don't have any {specialization} doctors available right now.",
                "data": None
            }
        
        # Check for "that doctor" reference
        text = entities.get("text", "").lower()
        if "that doctor" in text_lower and session and session.get("last_doctor_list"):
            # Reference the last mentioned doctor
            last_doctors = session["last_doctor_list"]
            if last_doctors:
                doctor_name = last_doctors[0]  # Use first mentioned doctor
                return {
                    "action": "doctor_info",
                    "response": f"Yes, I was referring to Dr. {doctor_name}.",
                    "data": {"doctors": doctors}
                }
        
        # Natural response with first doctor
        first_doctor = doctors[0]
        if len(doctors) == 1:
            response = f"Yes, Dr. {first_doctor['name']} is our {specialization} specialist."
        else:
            response = f"Yes, we have Dr. {first_doctor['name']} and {len(doctors)-1} other {specialization} specialists available."
        
        return {
            "action": "doctor_list",
            "response": response,
            "data": {"doctors": doctors}
        }

# Global instance
intent_service = IntentService()
