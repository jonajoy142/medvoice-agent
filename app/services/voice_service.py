from app.core.voice_pipeline import record_audio, transcribe_audio, speak
from app.services.llm_service import llm_service
from app.services.intent_service import intent_service
from app.core.logger import conversation_logger
from app.repo.mock_db import get_session, create_session, update_session
from typing import Dict, Any, Optional
import tempfile
import os

class VoiceService:
    def __init__(self):
        pass
    
    def process_voice(self, session_id: Optional[str] = None, voice: str = "female") -> Dict[str, Any]:
        """Process voice input with intent routing and logging"""
        
        # Get or create session
        if session_id:
            session = get_session(session_id)
            if not session:
                session = create_session(session_id)
        else:
            session_id = conversation_logger.generate_session_id()
            session = create_session(session_id)
        
        # Record audio
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                filename = temp_file.name
            
            file = record_audio(filename)
            
            if not file:
                return {
                    "session_id": session_id,
                    "status": "no_audio",
                    "message": "No speech detected",
                    "response": "I didn't hear anything. Please try again."
                }
            
            # Transcribe audio
            text = transcribe_audio(file)
            
            # Handle empty input - skip processing
            if not text:
                return {
                    "session_id": session_id,
                    "status": "no_transcription",
                    "message": "No speech detected",
                    "response": None  # Don't respond to empty input
                }
            
            # Detect intent and entities
            intent = intent_service.detect_intent(text)
            entities = intent_service.extract_entities(text)
            
            # Store OPID in session if detected
            if "opid" in entities and not session.get("opid"):
                update_session(session_id, {"opid": entities["opid"]})
                session["opid"] = entities["opid"]
                
                # Store patient name for better context
                from app.repo.mock_db import get_patient
                patient = get_patient(entities["opid"])
                if patient:
                    update_session(session_id, {"patient_name": patient["name"]})
                    session["patient_name"] = patient["name"]
            
            # Route intent with session context
            intent_result = intent_service.route_intent(intent, entities, session)
            
            # Generate contextual LLM response if needed
            if intent_result["action"] in ["general", "greet", "goodbye"]:
                # Use LLM for general conversation
                context = self._build_context(entities, session)
                reply = llm_service.generate_reply(
                    user_text=text,
                    history=session.get("conversation", []),
                    session_id=session_id,
                    context=context
                )
            else:
                # Use intent-based response
                reply = intent_result["response"]
                
                # Log the interaction only if there's a response
                if reply:
                    conversation_logger.log_interaction(
                        session_id=session_id,
                        user_text=text,
                        ai_response=reply,
                        intent=intent,
                        entities=entities,
                        action=intent_result["action"],
                        metadata={"data": intent_result["data"]}
                    )
            
            # Update session conversation only if there's a response
            if reply:
                conversation = session.get("conversation", [])
                conversation.append({"role": "user", "content": text})
                conversation.append({"role": "assistant", "content": reply})
                update_session(session_id, {"conversation": conversation})
            
            # Speak response (only if there's a response)
            if reply:
                try:
                    speak(reply, voice)
                except Exception as e:
                    # Silently handle TTS errors
                    pass
            
            # Clean up temp file
            try:
                os.unlink(file)
            except:
                pass
            
            return {
                "session_id": session_id,
                "status": "success",
                "user_input": text,
                "intent": intent,
                "entities": entities,
                "response": reply,
                "action": intent_result["action"],
                "data": intent_result["data"]
            }
            
        except Exception as e:
            error_msg = f"Voice processing error: {str(e)}"
            return {
                "session_id": session_id,
                "status": "error",
                "message": error_msg,
                "response": "Something went wrong. Please try again."
            }
    
    def _build_context(self, entities: Dict[str, Any], session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Build context for LLM"""
        context = {}
        
        # Add patient info if OPID found
        if "opid" in entities:
            from app.repo.mock_db import get_patient
            patient = get_patient(entities["opid"])
            if patient:
                context["patient"] = patient
                context["opid"] = entities["opid"]
        
        # Add doctor info if specialization found
        if "specialization" in entities:
            from app.repo.mock_db import get_doctors
            doctors = get_doctors(entities["specialization"])
            if doctors:
                context["doctors"] = doctors
        
        return context if context else None