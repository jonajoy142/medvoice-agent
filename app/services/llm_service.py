import requests
from typing import List, Dict, Any, Optional
from app.core.logger import conversation_logger
from app.core.config import settings

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
- Ask for OPID if needed
"""

class LLMService:
    def __init__(self, ollama_url: str = settings.ollama_url, model: str = settings.ollama_model):
        self.ollama_url = ollama_url
        self.model = model
        self.max_history = 3  # Keep last 3 exchanges for speed
    
    def generate_reply(self, 
                      user_text: str, 
                      history: List[Dict[str, str]], 
                      session_id: str,
                      context: Optional[Dict[str, Any]] = None) -> str:
        """Generate LLM reply with context and logging"""
        
        # Build conversation history
        history_text = self._build_history(history)
        
        # Build context information
        context_text = self._build_context(context)
        
        # Create prompt
        prompt = f"""
{SYSTEM_PROMPT}

{context_text}

Recent Conversation:
{history_text}

User: {user_text}
Assistant:
"""
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt.strip(),
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Lower temperature for more consistent responses
                        "max_tokens": 60,      # Reduce max tokens for faster, more natural responses
                        "top_p": 0.9,         # Reduce repetition
                        "repeat_penalty": 1.1   # Penalize repetition
                    }
                },
                timeout=settings.ollama_timeout_seconds
            )
            
            if response.status_code == 200:
                reply = response.json().get("response", "").strip()
                
                # Log the interaction
                conversation_logger.log_interaction(
                    session_id=session_id,
                    user_text=user_text,
                    ai_response=reply,
                    metadata={"context": context}
                )
                
                return reply
            else:
                error_msg = f"LLM service error: {response.status_code}"
                conversation_logger.log_interaction(
                    session_id=session_id,
                    user_text=user_text,
                    ai_response=error_msg,
                    metadata={"error": True, "status_code": response.status_code}
                )
                return "I'm having trouble connecting. Please try again."
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Connection error: {str(e)}"
            conversation_logger.log_interaction(
                session_id=session_id,
                user_text=user_text,
                ai_response=error_msg,
                metadata={"error": True, "exception": str(e)}
            )
            return "I'm having trouble connecting to the AI service. Please try again."
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            conversation_logger.log_interaction(
                session_id=session_id,
                user_text=user_text,
                ai_response=error_msg,
                metadata={"error": True, "exception": str(e)}
            )
            return "Something went wrong. Please try again."
    
    def _build_history(self, history: List[Dict[str, str]]) -> str:
        """Build conversation history string"""
        if not history:
            return "No previous conversation."
        
        # Take only the last N exchanges
        recent_history = history[-self.max_history:] if len(history) > self.max_history else history
        
        history_lines = []
        for msg in recent_history:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            if content:
                history_lines.append(f"{role.title()}: {content}")
        
        return "\n".join(history_lines)
    
    def _build_context(self, context: Optional[Dict[str, Any]]) -> str:
        """Build context information string"""
        if not context:
            return "No specific context available."
        
        context_parts = []
        
        if "patient" in context:
            patient = context["patient"]
            context_parts.append(f"Current Patient: {patient.get('name', 'Unknown')} (OPID: {context.get('opid', 'Unknown')})")
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
        """Check if Ollama service is available"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False

# Global LLM service instance
llm_service = LLMService()