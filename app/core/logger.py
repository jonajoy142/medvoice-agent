"""
Logging system for MedVoice AI conversations
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
import uuid
import re

from app.core.config import settings

class ConversationLogger:
    def __init__(self, log_dir: str = "logs", redact_phi: bool = True):
        self.log_dir = log_dir
        self.log_file = os.path.join(log_dir, "conversations.log")
        self.redact_phi = redact_phi
        
        # Create logs directory if it doesn't exist
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
    
    def log_interaction(self, 
                       session_id: str,
                       user_text: str,
                       ai_response: str,
                       intent: Optional[str] = None,
                       entities: Optional[Dict[str, Any]] = None,
                       action: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log a conversation interaction"""
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "user_text": self._redact_text(user_text),
            "ai_response": self._redact_text(ai_response),
            "intent": intent,
            "entities": self._redact_entities(entities),
            "action": action,
            "metadata": self._redact_dict(metadata or {}),
        }
        
        # Append to log file
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    
    def get_conversation_history(self, session_id: str, limit: int = 10) -> list:
        """Get conversation history for a session"""
        if not os.path.exists(self.log_file):
            return []
        
        history = []
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry.get("session_id") == session_id:
                            history.append(entry)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error reading log file: {e}")
        
        # Return last N entries
        return history[-limit:] if history else []
    
    def get_all_sessions(self) -> list:
        """Get all unique session IDs"""
        if not os.path.exists(self.log_file):
            return []
        
        sessions = set()
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if "session_id" in entry:
                            sessions.add(entry["session_id"])
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error reading log file: {e}")
        
        return list(sessions)
    
    def generate_session_id(self) -> str:
        """Generate a new session ID"""
        return str(uuid.uuid4())

    def _redact_text(self, text: str) -> str:
        if not self.redact_phi or not text:
            return text
        redacted = re.sub(r"\b\d{6}\b", "[REDACTED_OPID]", text)
        redacted = re.sub(r"(\+?\d[\d\-\s]{7,}\d)", "[REDACTED_PHONE]", redacted)
        return redacted

    def _redact_entities(self, entities: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if entities is None:
            return None
        return self._redact_dict(entities)

    def _redact_dict(self, value: Any) -> Any:
        if not self.redact_phi:
            return value
        if isinstance(value, dict):
            return {key: self._redact_dict(val) for key, val in value.items()}
        if isinstance(value, list):
            return [self._redact_dict(item) for item in value]
        if isinstance(value, str):
            return self._redact_text(value)
        return value

# Global logger instance
conversation_logger = ConversationLogger(log_dir=settings.log_dir, redact_phi=settings.log_redact_phi)
